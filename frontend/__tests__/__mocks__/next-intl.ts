const React = require("react");
const messages = require("../../messages/en.json");

function useTranslations(namespace: string) {
  const ns = (messages as Record<string, Record<string, string>>)[namespace] || {};
  function t(key: string, values?: Record<string, unknown>) {
    let result = ns[key] || key;
    if (values) {
      Object.entries(values).forEach(([k, v]) => {
        result = result.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
      });
    }
    return result;
  }
  t.has = function (key: string) {
    return key in ns;
  };
  return t;
}

function useLocale() {
  return "en";
}

function NextIntlClientProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

module.exports = {
  useTranslations,
  useLocale,
  NextIntlClientProvider,
};
