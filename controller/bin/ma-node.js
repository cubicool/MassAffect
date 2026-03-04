#!/usr/bin/env -S node --experimental-repl-await

import repl from "repl";

import { createClient } from 'redis';

const redis = createClient();

await redis.connect();

import { cfg } from "../src/config.js";
import { Events } from "../src/lib.js";

const r = repl.start({
	prompt: "massaffect> ",
	useGlobal: false
});

r.context.cfg = cfg;
r.context.config = cfg();
r.context.Events = Events;
r.context.redis = redis;

// console.log("Interactive shell ready. Try config.controller or cfg()");
