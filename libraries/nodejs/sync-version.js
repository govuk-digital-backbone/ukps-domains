#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

// path to your JSON file
const domainsPath = path.resolve(__dirname, "../../data/user_domains.json");
const pkgPath = path.resolve(__dirname, "package.json");

// read version from user_domains.json
const domains = JSON.parse(fs.readFileSync(domainsPath, "utf8"));
const version = domains.version;

if (!version) {
  console.error("No version field found in user_domains.json");
  process.exit(1);
}

// update package.json version
const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
pkg.version = version;

fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + "\n");

console.log(`package.json updated to version ${version}`);
