const messages = require("../../messages/en.json");

async function getTranslations(namespace: string) {
  const ns = (messages as Record<string, Record<string, string>>)[namespace] || {};
  return function t(key: string, values?: Record<string, unknown>) {
    let result = ns[key] || key;
    if (values) {
      Object.entries(values).forEach(([k, v]) => {
        result = result.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
      });
    }
    return result;
  };
}

async function getMessages() {
  return messages;
}

module.exports = {
  getTranslations,
  getMessages,
};
