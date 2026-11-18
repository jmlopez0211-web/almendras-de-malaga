require('dotenv').config();
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const Stripe = require('stripe');
const catalog = require('./catalog.json');

const app = express();
const PORT = Number(process.env.PORT || 4242);
const stripeKey = process.env.STRIPE_SECRET_KEY || '';
const stripe = stripeKey.startsWith('sk_') ? new Stripe(stripeKey) : null;
const allowedOrigin = process.env.ALLOWED_ORIGIN || 'https://jmlopez0211-web.github.io';
const siteUrl = (process.env.SITE_URL || 'https://jmlopez0211-web.github.io/almendras-de-malaga').replace(/\/$/, '');

app.disable('x-powered-by');
app.use(helmet());
app.use(cors({ origin: allowedOrigin, methods: ['GET', 'POST'], allowedHeaders: ['Content-Type'] }));
app.use(express.json({ limit: '20kb' }));
app.use('/api/', rateLimit({ windowMs: 15 * 60 * 1000, limit: 30, standardHeaders: true, legacyHeaders: false }));

app.get('/health', (_req, res) => res.json({ ok: true, service: 'almendras-checkout' }));

app.post('/api/create-checkout-session', async (req, res) => {
  try {
    if (process.env.PAYMENTS_ENABLED !== 'true') {
      return res.status(503).json({ error: 'El pago con tarjeta todavía no está activado. Contacta con la tienda para confirmar el pedido.' });
    }
    if (!stripe) return res.status(503).json({ error: 'El servidor de pagos no está configurado.' });

    const { items, customer, notes = '' } = req.body || {};
    if (!Array.isArray(items) || items.length < 1 || items.length > 30) {
      return res.status(400).json({ error: 'El carrito no es válido.' });
    }
    const name = String(customer?.name || '').trim().slice(0, 100);
    const phone = String(customer?.phone || '').trim().slice(0, 30);
    if (!name || !phone) return res.status(400).json({ error: 'Indica nombre y teléfono.' });

    const line_items = items.map((item) => {
      const product = catalog.find((p) => p.id === item.id);
      const grams = Number(item.grams);
      const quantity = Number(item.quantity);
      if (!product || ![100, 250, 500, 1000].includes(grams) ||
          !Number.isInteger(quantity) || quantity < 1 || quantity > 50) {
        throw new Error('Hay un producto, formato o cantidad no válida.');
      }
      const unitAmount = Math.round(product.pricePerKg * grams / 1000 * 100);
      if (unitAmount < 50) throw new Error('El importe mínimo por formato no es válido.');
      return {
        quantity,
        price_data: {
          currency: 'eur',
          unit_amount: unitAmount,
          product_data: {
            name: product.name + ' · ' + grams + ' g',
            metadata: { product_id: product.id, grams: String(grams) }
          }
        }
      };
    });

    const session = await stripe.checkout.sessions.create({
      mode: 'payment',
      line_items,
      success_url: siteUrl + '/?payment=success&session_id={CHECKOUT_SESSION_ID}',
      cancel_url: siteUrl + '/?payment=cancelled',
      customer_creation: 'always',
      phone_number_collection: { enabled: true },
      billing_address_collection: 'auto',
      metadata: {
        customer_name: name,
        customer_phone: phone,
        order_notes: String(notes).slice(0, 400)
      }
    });
    return res.json({ url: session.url });
  } catch (error) {
    console.error('Checkout error:', error.message);
    return res.status(400).json({ error: error.message || 'No se pudo crear el pago.' });
  }
});

app.listen(PORT, () => console.log('Checkout server listening on port ' + PORT));
