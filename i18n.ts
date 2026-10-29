import { locales } from "middleware";
import { getRequestConfig } from "next-intl/server";
import { notFound } from "next/navigation";
import deepmerge from "deepmerge";

export default getRequestConfig(async ({ requestLocale }) => {
  const locale = (await requestLocale) ?? "en";
  // Validate that the incoming `locale` parameter is valid
  if (!locales.includes(locale as any)) notFound();

  const userMessages = (await import(`./messages/${locale}.json`)).default;
  const defaultMessages = (await import(`./messages/en.json`)).default;
  const messages = deepmerge(defaultMessages, userMessages);
  return { locale, messages };
});
