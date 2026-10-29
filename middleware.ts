import { NextRequest, NextResponse } from "next/server";

// Language names are not translated because we want them to be the same always, regardless of the current language.
// *** IMPORTANT *** Add  new languages to the localeData and matcher in the config below
export const localeData = {
  cs: "Čeština",
  da: "Dansk",
  de: "Deutsch",
  en: "English",
  es: "Español",
  fr: "Français",
  hu: "Magyar",
  it: "Italiano",
  "nb-NO": "Norwegian Bokmål", // Needs to be in format nb-NO instead of nb_NO for next-intl to recognize it
  nl: "Nederlands",
  sl: "Slovenščina",
  sv: "Svenska",
  ta: "தமிழ்",
};

export const locales = Object.keys(localeData);

export default function middleware(request: NextRequest) {
  const prefix = request.nextUrl.pathname.split("/")[1];
  if (!locales.includes(prefix)) {
    const preferred = request.cookies.get("NEXT_LOCALE")?.value;
    const locale = preferred && locales.includes(preferred) ? preferred : "en";
    const url = request.nextUrl.clone();
    url.pathname = `/${locale}${request.nextUrl.pathname === "/" ? "" : request.nextUrl.pathname}`;
    return NextResponse.redirect(url);
  }
  // The locale is already an App Router segment. Pass it to next-intl without
  // rewriting the same URL through localhost (which can recurse on loopback hosts).
  const headers = new Headers(request.headers);
  headers.set("X-NEXT-INTL-LOCALE", prefix);
  const response = NextResponse.next({ request: { headers } });
  response.cookies.set("NEXT_LOCALE", prefix, { sameSite: "lax", path: "/" });
  return response;
}

export const config = {
  // Match only internationalized pathnames
  // Match /calibrate for people who saved a link to /calibrate before internationalization was added
  // *** IMPORTANT *** New language codes must be added here as well as in the localeData above
  matcher: [
    "/",
    "/(cs|da|de|en|es|fr|hu|it|nb-NO|nl|sl|sv|ta)/:path*",
    "/calibrate",
  ],
};
