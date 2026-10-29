// Use type safe message keys with `next-intl`
type Messages = typeof import("./messages/en.json");
declare interface IntlMessages extends Messages {}

interface Window {
  launchQueue?: {
    setConsumer: (
      consumer: (params: { files: FileSystemHandle[] }) => Promise<void>,
    ) => void;
  };
}
