import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync(new URL("../js/commercial-config.js", import.meta.url), "utf8");

function createContext(fetchImplementation) {
  const events = [];
  const window = {
    dispatchEvent(event) { events.push(event); }
  };
  const context = {
    window,
    fetch: fetchImplementation,
    CustomEvent: class {
      constructor(type, options = {}) {
        this.type = type;
        this.detail = options.detail;
      }
    },
    console: { warn() {} }
  };
  vm.runInNewContext(source, context);
  return { window, events };
}

const validConfig = {
  business: "Almendras de Málaga",
  shipping: {
    status: "provisional",
    note: "Pendiente de confirmar",
    tiers: [
      { maxGrams: 100, label: "Hasta 100 g", price: 1 },
      { maxGrams: 250, label: "101–250 g", price: 2 },
      { maxGrams: 500, label: "251–500 g", price: 3 },
      { maxGrams: 1000, label: "501 g–1 kg", price: 4 },
      { maxGrams: 5000, label: "1,001–5 kg", price: 5 },
      { maxGrams: 10000, label: "5,001–10 kg", price: 6 },
      { maxGrams: 20000, label: "10,001–20 kg", price: 7 },
      { maxGrams: null, label: "Más de 20 kg", price: 8 }
    ]
  }
};

test("loads and validates the commercial JSON as the shared source", async () => {
  const { window, events } = createContext(async () => ({
    ok: true,
    json: async () => validConfig
  }));

  const loaded = await window.COMMERCIAL_CONFIG_READY;
  assert.equal(loaded.shipping.tiers[0].price, 1);
  assert.equal(window.COMMERCIAL_CONFIG.shipping.tiers[7].maxGrams, null);
  assert.equal(events.length, 1);
  assert.equal(events[0].type, "almendras:commercial-config-updated");
  assert.equal(events[0].detail.source, "data/commercial.json");
});

test("keeps fallback configuration when the request fails", async () => {
  const { window, events } = createContext(async () => ({
    ok: false,
    status: 503
  }));

  const loaded = await window.COMMERCIAL_CONFIG_READY;
  assert.equal(loaded.shipping.tiers.length, 8);
  assert.equal(loaded.shipping.tiers[0].price, 2.5);
  assert.equal(events[0].detail.source, "fallback");
});

test("rejects invalid shipping thresholds and uses the safe fallback", async () => {
  const invalid = structuredClone(validConfig);
  invalid.shipping.tiers[2].maxGrams = 200;
  const { window } = createContext(async () => ({
    ok: true,
    json: async () => invalid
  }));

  const loaded = await window.COMMERCIAL_CONFIG_READY;
  assert.equal(loaded.shipping.tiers[0].price, 2.5);
  assert.equal(loaded.shipping.tiers[1].price, 3.5);
});

test("rejects negative prices and a non-open final shipping tier", async () => {
  for (const mutate of [
    config => { config.shipping.tiers[1].price = -1; },
    config => { config.shipping.tiers[7].maxGrams = 50000; }
  ]) {
    const invalid = structuredClone(validConfig);
    mutate(invalid);
    const { window } = createContext(async () => ({
      ok: true,
      json: async () => invalid
    }));
    const loaded = await window.COMMERCIAL_CONFIG_READY;
    assert.equal(loaded.shipping.tiers[0].price, 2.5);
  }
});
