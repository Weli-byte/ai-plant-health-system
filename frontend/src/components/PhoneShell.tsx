import { ReactNode } from "react";

/**
 * Mobil-first kabuk. Desktop'ta ortada bir telefon çerçevesi gibi durur.
 */
export function PhoneShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh w-full bg-earth-gradient sm:py-6">
      <div className="phone-frame">{children}</div>
    </div>
  );
}
