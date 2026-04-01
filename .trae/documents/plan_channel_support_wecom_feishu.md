# Plan: Support WeCom and Feishu Bot Channels

## Goal
Add support for sending messages via Enterprise WeChat (WeCom) and Feishu (Lark) bots in the Channel module.

## Current State
- Backend `ChannelService` supports `dingtalk` and `qqbot`.
- Frontend `operate-modal.vue` has form fields for `dingtalk` and `qqbot`.
- `ChannelType` enum includes `wechat_work` and `feishu` but they are not implemented.

## Proposed Changes

### Backend
1.  **Create `backend/app/core/channel/wechat_work.py`**:
    - Implement `WechatWorkAdapter` inheriting from `BaseAdapter`.
    - Support `send_text` and `send_markdown` using WeCom Webhook API.
    - Config: `webhook_url`.

2.  **Create `backend/app/core/channel/feishu.py`**:
    - Implement `FeishuAdapter` inheriting from `BaseAdapter`.
    - Support `send_text` and `send_markdown` using Feishu Custom Bot API.
    - Support signature verification (timestamp + sign).
    - Config: `webhook_url`, `secret` (optional).

3.  **Update `backend/app/core/channel/factory.py`**:
    - Register `wechat_work` and `feishu` adapters.

### Frontend
1.  **Update `frontend/packages/web/src/pages/channel/components/operate-modal.vue`**:
    - Add form fields for `wechat_work` (Webhook URL).
    - Add form fields for `feishu` (Webhook URL, Secret).
    - Update validation logic for new types.

## Verification
1.  **Backend Unit/Integration Tests**:
    - Verify `WechatWorkAdapter` sends correct payload.
    - Verify `FeishuAdapter` generates correct signature and payload.
2.  **Frontend Manual Test**:
    - Create a WeCom channel and send a test message.
    - Create a Feishu channel and send a test message.

## Assumptions
- WeCom uses Group Bot Webhook (key-based).
- Feishu uses Custom Bot Webhook (v2).
