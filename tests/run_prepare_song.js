#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const { prepareSong } = require(path.join(__dirname, "..", "demo", "js", "prepare_song.js"));

const input = fs.readFileSync(0, "utf8");
const addData = process.argv.includes("--data-attr");
process.stdout.write(JSON.stringify(prepareSong(input, addData)));
