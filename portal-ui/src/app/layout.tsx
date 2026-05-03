import type { Metadata } from "next";
import "@mantine/core/styles.css";
import { ColorSchemeScript, MantineProvider, createTheme } from "@mantine/core";

export const metadata: Metadata = {
  title: "Orbiteus Portal",
  description: "External partner portal for shared resources.",
};

const theme = createTheme({
  primaryColor: "dark",
  fontFamily: "Inter, system-ui, sans-serif",
  defaultRadius: "md",
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <ColorSchemeScript defaultColorScheme="light" />
      </head>
      <body>
        <MantineProvider theme={theme} defaultColorScheme="light">
          {children}
        </MantineProvider>
      </body>
    </html>
  );
}
