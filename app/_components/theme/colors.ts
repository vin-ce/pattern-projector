import { ButtonStyle } from "./styles";

export enum ButtonColor {
  BLUE = "blue",
  GRAY = "gray",
  PURPLE = "purple",
}

export enum IconButtonStateClass {
  DEFAULT = "",
  ACTIVE = "!bg-black text-white dark:!bg-white dark:!text-black hover:bg-gray-800 focus:ring-gray-500",
  DISABLED = "text-gray-400 dark:text-gray-600 cursor-not-allowed",
}

export function getColorClasses(
  color: ButtonColor = ButtonColor.PURPLE,
  style: ButtonStyle = ButtonStyle.OUTLINE,
) {
  switch (color) {
    case ButtonColor.BLUE: {
      return style === ButtonStyle.OUTLINE
        ? "text-blue-700 border-blue-700 hover:bg-blue-800 focus:ring-blue-300 dark:border-blue-500 dark:text-blue-500 dark:hover:bg-blue-500 dark:focus:ring-blue-800"
        : "bg-blue-700 hover:bg-blue-800 focus:ring-blue-300 dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800";
    }
    case ButtonColor.GRAY: {
      return style === ButtonStyle.OUTLINE
        ? "text-black border-gray-700 hover:bg-gray-800 focus:ring-gray-300 dark:border-gray-500 dark:text-gray-500 dark:hover:bg-gray-500 dark:focus:ring-gray-800"
        : "bg-black hover:bg-gray-800 focus:ring-gray-300 dark:bg-gray-600 dark:hover:bg-gray-700 dark:focus:ring-gray-800";
    }
    case ButtonColor.PURPLE: {
      return style === ButtonStyle.OUTLINE
        ? "text-black border-black hover:bg-black focus:ring-gray-300 dark:border-white dark:text-white dark:hover:bg-gray-700 dark:focus:ring-gray-800"
        : "bg-black hover:bg-gray-800 focus:ring-gray-300 dark:bg-gray-700 dark:hover:bg-gray-800 dark:focus:ring-gray-800";
    }
  }
}
