#!/usr/bin/env node
"use strict";
const { join } = require("path");
const { readFileSync } = require("fs");
const { URL } = require("url");

// UKPSDomains class
class UKPSDomains {
  constructor(options = {}) {
    this._debug = options.debug || false;

    this._allow_remote =
      options.allow_remote !== null || options.allow_remote !== undefined
        ? options.allow_remote
        : true;
    this._remote_url_prefix =
      "https://raw.githubusercontent.com/govuk-digital-backbone/ukps-domains/refs/heads/main/data/";
    this._remote_timeout_ms = 2000;

    this._local_directory = options.local_directory || __dirname;
    if (this._debug) {
      console.log(`Local directory set to: ${this._local_directory}`);
    }

    this._insecure = options.insecure || false;
    if (this._insecure) {
      // This is an awful way of disabling certificate validation
      process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
    }

    this._status = {
      "user_domains.json": null,
      "govuk_organisations.json": null,
    };

    this.refresh();
  }

  ready() {
    return (
      this._status["user_domains.json"] !== null &&
      this._status["govuk_organisations.json"] !== null
    );
  }

  async refresh() {
    this._status = {
      "user_domains.json": null,
      "govuk_organisations.json": null,
    };
    this._data = {};
    this._data["user_domains.json"] = {};
    this._user_domains_source = await this._getFile("user_domains.json");
    this._data["govuk_organisations.json"] = {};
    this._govuk_organisations_source = await this._getFile(
      "govuk_organisations.json"
    );
  }

  async _getFile(fileName) {
    const fileUrl = this._remote_url_prefix + fileName;
    const controller = new AbortController();
    const timeout = setTimeout(
      () => controller.abort(),
      this._remote_timeout_ms
    );

    if (this._allow_remote) {
      if (this._debug) {
        console.log(`Fetching remote file: ${fileUrl}`);
      }
      const res = await fetch(fileUrl, { signal: controller.signal });
      if (res.ok) {
        const data = await res.json();
        if (data) {
          this._data[fileName] = data;
          this._status[fileName] = "remote";
        }
      }
    }

    if (this._status[fileName] === null) {
      const localPath = join(this._local_directory, fileName);
      if (this._debug) {
        console.log(`Attempting to load local file: ${localPath}`);
      }
      const fileData = JSON.parse(readFileSync(localPath, "utf8"));
      this._data[fileName] = fileData;
      this._status[fileName] = "local";
    }
  }

  _getDomains() {
    if (!this.ready()) {
      throw new Error("Data not ready or not available");
    }
    return this._data["user_domains.json"].domains || [];
  }

  _normaliseDomain(domain) {
    let resDomain = null;
    if (domain !== null && domain !== undefined) {
      resDomain = domain.trim().toLowerCase().replace(/\.+$/, "");
    }
    if (resDomain === null || !resDomain.includes(".")) {
      throw new Error("Domain invalid");
    }
    return resDomain;
  }

  _extractDomainFromEmail(email) {
    if (!email || email.indexOf("@") === -1) {
      return null;
    }
    return email.split("@").pop().toLowerCase().trim();
  }

  isUKPSEmail(email) {
    const ctx = this.organisationalContextForEmail(email, false);
    return ctx !== null;
  }

  isUKPSDomain(domain) {
    const ctx = this.organisationalContextForDomain(domain, false);
    return ctx !== null;
  }

  organisationalContextForEmail(inputEmail, withGovukData = true) {
    const domain = this._extractDomainFromEmail(inputEmail);
    return this.organisationalContextForDomain(domain, withGovukData);
  }

  organisationalContextForDomain(inputDomain, withGovukData = true) {
    const domain = this._normaliseDomain(inputDomain);
    const domains = this._getDomains();
    let context = domains.find((entry) => entry.domain_pattern === domain);

    if (!context) {
      context = domains.find((entry) => {
        const pattern = entry.domain_pattern || "";
        if (pattern.startsWith("*.") && domain.endsWith(pattern.slice(1))) {
          return true;
        }
      });
    }

    if (context && context.organisation_id && withGovukData) {
      const orgs = this._data["govuk_organisations.json"] || {};
      if (context.organisation_id in orgs) {
        context.govuk_data = orgs[context.organisation_id];
      }
    }

    return context || null;
  }
}

module.exports = { UKPSDomains };
