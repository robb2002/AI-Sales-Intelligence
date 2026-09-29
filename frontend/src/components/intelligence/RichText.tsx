import { Fragment } from "react";

/** Safe inline formatting: **bold** only. Emoji and other text pass through as plain text. */
export function RichText({
  text,
  strongClassName = "font-semibold",
}: {
  text: string;
  strongClassName?: string;
}) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, index) => {
        if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
          return (
            <strong key={index} className={strongClassName}>
              {part.slice(2, -2)}
            </strong>
          );
        }
        return <Fragment key={index}>{part}</Fragment>;
      })}
    </>
  );
}
