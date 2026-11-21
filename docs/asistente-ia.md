# Almendras de Málaga AI Assistant

Secure backend for the website chat and WhatsApp Business Cloud API.

## Endpoints
- GET /health: service status (never exposes secrets).
- POST /api/chat: website chat. JSON: {"session_id":"...","message":"..."}.
- GET /webhook/whatsapp: Meta webhook verification.
- POST /webhook/whatsapp: signed WhatsApp event processing.

## Environment
- OPENAI_API_KEY (required for AI)
- OPENAI_MODEL (defaults to gpt-6.2-sol)
- WHATSAPP_ACCESS_TOKEN
- WHATSAPP_PHONE_NUMBER_ID
- WHATSAPP_VERIFY_TOKEN (a random secret you choose)
- WHATSAPP_APP_SECRET (Meta app secret; validates webhook signatures)
- WHATSAPP_API_VERSION (current Graph API version, e.g. vXX.X)

Never put tokens or API keys in the website JavaScript or GitHub.

## Deploy
Use the included render.yaml Blueprint. Add secrets in Render Environment. The service uses the repository catalog as its source of truth.

## WhatsApp setup
1. Create/choose a Meta Business app and WhatsApp Business account.
2. Configure WhatsApp Cloud API and obtain a phone number ID and access token.
3. Set webhook URL to https://YOUR-SERVICE.onrender.com/webhook/whatsapp.
4. Set the same random verify token in Meta and Render.
5. Subscribe to the messages webhook field.
6. Configure app secret and API version in Render.
7. Test with Meta's test number before enabling the business number.

The initial version uses bounded in-memory chat history. For production scaling, add persistent storage, delivery logs, opt-out handling, human handoff and order records.
