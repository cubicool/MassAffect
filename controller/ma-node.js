#!/usr/bin/env -S node --experimental-repl-await

import repl from "repl";
import { cfg } from "./config.js";

const r = repl.start({
	prompt: "massaffect> ",
	useGlobal: false
});

r.context.cfg = cfg;
r.context.config = cfg();

// console.log("Interactive shell ready. Try config.controller or cfg()");
