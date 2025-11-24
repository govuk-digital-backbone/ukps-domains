const { join } = require("path");
const assert = require("assert");
const { UKPSDomains } = require("./index.js");

(async () => {
  try {
    const d1 = new UKPSDomains({
      allow_remote: false,
      debug: true,
      local_directory: join(__dirname, "../../data/"),
    });
    await d1.refresh();
    assert.ok(
      d1._status["user_domains.json"] === "local",
      "Local user_domains.json not loaded"
    );
    assert.ok(
      d1._status["govuk_organisations.json"] === "local",
      "Local govuk_organisations.json not loaded"
    );
    console.log("OK: local files loaded");
  } catch (err) {
    console.error("TEST FAILED:", err.message);
    process.exit(1);
  }
})();

(async () => {
  try {
    const d3 = new UKPSDomains({
      allow_remote: true,
      insecure: true,
      debug: true,
      local_directory: __dirname,
    });
    await d3.refresh();
    assert.ok(
      d3._status["user_domains.json"] === "remote",
      "Remote user_domains.json not loaded"
    );
    console.log("OK: remote user_domains.json loaded");
  } catch (err) {
    console.error("TEST FAILED:", err.message);
    process.exit(1);
  }
})();
