import { Anchor, Container, Stack, Text, Title } from "@mantine/core";

export default function PortalRoot() {
  return (
    <Container size="sm" py="xl">
      <Stack gap="md">
        <Title order={1}>Orbiteus Partner Portal</Title>
        <Text c="dimmed">
          This is the entry point for external collaborators. Open the share
          link you received in your email to view the resource.
        </Text>
        <Text size="sm" c="dimmed">
          If you don&apos;t have a share link, contact your account
          administrator.
        </Text>
        <Anchor href="https://orbiteus.com" target="_blank" rel="noreferrer">
          About Orbiteus
        </Anchor>
      </Stack>
    </Container>
  );
}
