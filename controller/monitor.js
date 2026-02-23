import express from "express";
import crypto from "crypto";

export default function monitorRoutes(redis) {
    const router = express.Router();

    const ALLOWED_IPS = new Set([
        "127.0.0.1",
        "::1",
        "104.13.36.111"
    ]);

    const clients = new Set(); // Active SSE connections

    function verifyIP(req, res, next) {
        const ip = req.ip.replace("::ffff:", "");
        console.log("verifyIP:", ip);
        if (!ALLOWED_IPS.has(ip)) {
            console.log("verifyIP failure:", ip);
            return res.status(403).json({ error: "Forbidden" });
        }
        next();
    }

    function verifyHMAC(req, res, next) {
        const SECRET = process.env.AGENT_SECRET;
        const signature = req.headers["x-agent-signature"];
        const body = JSON.stringify(req.body);

        const expected = crypto
            .createHmac("sha256", SECRET)
            .update(body)
            .digest("hex");

        if (!signature || signature.length !== expected.length) {
            return res.status(401).json({ error: "Invalid signature" });
        }

        const safe = crypto.timingSafeEqual(
            Buffer.from(signature),
            Buffer.from(expected)
        );

        if (!safe) {
            return res.status(401).json({ error: "Invalid signature" });
        }

        next();
    }

    router.use(verifyIP);

    // --- SSE STREAM ---
    router.get("/stream", (req, res) => {
        res.setHeader("Content-Type", "text/event-stream");
        res.setHeader("Cache-Control", "no-cache");
        res.setHeader("Connection", "keep-alive");
        res.flushHeaders?.();

        res.write(`data: ${JSON.stringify({ status: "connected" })}\n\n`);

        clients.add(res);

        req.on("close", () => {
            clients.delete(res);
        });
    });

    // --- POST collector endpoint ---
    router.post("/system", verifyHMAC, async (req, res) => {
        console.log("Received system metrics:", req.body.hostname);

        const payload = req.body;
        const id = Date.now().toString();

        await redis.set(`collector:${id}`, JSON.stringify(payload));
        await redis.lPush("collector:index", id);
        await redis.lTrim("collector:index", 0, 99);

        // Broadcast to all live viewers
        const message = `data: ${JSON.stringify({ id, payload })}\n\n`;
        for (const client of clients) {
            client.write(message);
        }

        res.json({ ok: true });
    });

    // --- GET viewer (history + live updates) ---
    router.get("/", async (req, res) => {
        try {
            const ids = await redis.lRange("collector:index", 0, 19);

            const items = await Promise.all(
                ids.map(id => redis.get(`collector:${id}`))
            );

            const parsed = items
                .filter(Boolean)
                .map(item => JSON.parse(item));

            res.type("html").send(`
                <html>
                <body style="background:#111;color:#0f0;font-family:monospace;padding:20px;">
                <h2>MassAffect Collector (Live)</h2>
                <pre id="output">${JSON.stringify(parsed, null, 2)}</pre>

                <script>
                    const output = document.getElementById("output");
                    const evtSource = new EventSource("/monitor/stream");

                    evtSource.onmessage = function(event) {
                        const data = JSON.parse(event.data);

                        // Ignore initial "connected" message
                        if (data.payload) {
                            output.textContent =
                                JSON.stringify(data.payload, null, 2)
                                + "\\n\\n"
                                + output.textContent;
                        }
                    };
                </script>

                </body>
                </html>
            `);
        } catch (err) {
            console.error("Monitor GET error:", err);
            res.status(500).json({ error: "Failed to load monitor data" });
        }
    });

    return router;
}
