"use client";

import { Drawer, Stack, Title } from "@mantine/core";

import { PromptInput } from "./PromptInput";
import type { AIScope } from "./types";

interface Props {
  scope: AIScope;
  opened: boolean;
  onClose: () => void;
  title?: string;
}

/** Drawer-style chat panel built on top of `<PromptInput>`. */
export function AIChatPanel({ scope, opened, onClose, title = "Assistant" }: Props) {
  return (
    <Drawer position="right" size="md" opened={opened} onClose={onClose} withCloseButton>
      <Stack gap="md" h="100%">
        <Title order={4}>{title}</Title>
        <PromptInput scope={scope} />
      </Stack>
    </Drawer>
  );
}
