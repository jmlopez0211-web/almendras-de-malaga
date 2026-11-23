/* Configuración comercial compartida por la tienda y el asistente. */
(function () {
  "use strict";

  const DEFAULT_TIERS = [
    { maxGrams: 100, label: "Hasta 100 g", price: 2.5 },
    { maxGrams: 250, label: "101–250 g", price: 3.5 },
    { maxGrams: 500, label: "251–500 g", price: 4.5 },
    { maxGrams: 1000, label: "501 g–1 kg", price: 5.5 },
    { maxGrams: 5000, label: "1,001–5 kg", price: 7.5 },
    { maxGrams: 10000, label: "5,001–10 kg", price: 9.5 },
    { maxGrams: 20000, label: "10,001–20 kg", price: 12.5 },
    { maxGrams: null, label: "Más de 20 kg", price: 15 }
  ];

  const fallback = {
    business: "Almendras de Málaga",
    shipping: {
      status: "provisional",
      note: "Tarifas de envío provisionales; confirmar con el transportista.",
      tiers: DEFAULT_TIERS.map(tier => ({ ...tier }))
    }
  };

  function validateCommercialConfig(config) {
    if (!config || typeof config !== "object" || Array.isArray(config)) {
      throw new Error("La configuración comercial debe ser un objeto.");
    }
    const tiers = config.shipping && config.shipping.tiers;
    if (!Array.isArray(tiers) || tiers.length !== DEFAULT_TIERS.length) {
      throw new Error("La configuración debe contener exactamente ocho tramos de envío.");
    }

    let previousMaximum = 0;
    const normalizedTiers = tiers.map((tier, index) => {
      if (!tier || typeof tier !== "object") {
        throw new Error("Tramo de envío inválido en la posición " + index + ".");
      }
      const label = String(tier.label || "").trim();
      const price = Number(tier.price);
      const isLast = index === tiers.length - 1;
      const maxGrams = tier.maxGrams == null ? null : Number(tier.maxGrams);

      if (!label || !Number.isFinite(price) || price < 0) {
        throw new Error("Etiqueta o precio inválido en el tramo " + index + ".");
      }
      if (isLast) {
        if (maxGrams !== null) {
          throw new Error("El último tramo debe ser abierto (maxGrams: null).");
        }
      } else {
        if (!Number.isFinite(maxGrams) || maxGrams <= previousMaximum) {
          throw new Error("Los límites de envío deben ser positivos y estrictamente crecientes.");
        }
        previousMaximum = maxGrams;
      }
      return { maxGrams, label, price };
    });

    return {
      ...config,
      shipping: {
        ...config.shipping,
        tiers: normalizedTiers
      }
    };
  }

  window.COMMERCIAL_CONFIG = fallback;
  window.COMMERCIAL_CONFIG_READY = fetch("data/commercial.json", {
    headers: { Accept: "application/json" }
  })
    .then(response => {
      if (!response.ok) {
        throw new Error("No se pudo cargar data/commercial.json (HTTP " + response.status + ").");
      }
      return response.json();
    })
    .then(validateCommercialConfig)
    .then(config => {
      window.COMMERCIAL_CONFIG = config;
      window.dispatchEvent(new CustomEvent("almendras:commercial-config-updated", {
        detail: { source: "data/commercial.json", status: config.shipping.status || "provisional" }
      }));
      return config;
    })
    .catch(error => {
      console.warn("Se mantienen las tarifas comerciales de respaldo:", error.message);
      window.dispatchEvent(new CustomEvent("almendras:commercial-config-updated", {
        detail: { source: "fallback", error: error.message }
      }));
      return window.COMMERCIAL_CONFIG;
    });
})();
