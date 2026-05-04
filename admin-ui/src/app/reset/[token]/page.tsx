"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Alert,
  Anchor,
  Box,
  Button,
  Card,
  Container,
  Group,
  PasswordInput,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle, IconCircleCheck } from "@tabler/icons-react";
import { api } from "@/lib/api";

/**
 * Confirm-reset page consumed via the link from the password-reset email.
 *
 * URL shape: `/reset/<jwt>` — the `proxy.ts` matcher whitelists the
 * `/reset/` prefix so unauthenticated visitors can land here.
 */
export default function ResetPasswordPage() {
  const router = useRouter();
  const params = useParams<{ token: string }>();
  const token = typeof params?.token === "string" ? params.token : "";

  const [pw1, setPw1] = useState("");
  const [pw2, setPw2] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (pw1.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (pw1 !== pw2) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await api.post("/auth/password/reset", {
        token,
        new_password: pw1,
      });
      setSuccess(true);
      setTimeout(() => router.push("/login"), 1500);
    } catch (err: unknown) {
      // Backend returns 401 for invalid/expired/already-used tokens
      // and 400 for too-short passwords. Anything else is a 500.
      let message = "Could not reset password. The link may have expired.";
      if (typeof err === "object" && err !== null && "response" in err) {
        const r = (err as { response?: { data?: { detail?: string } } }).response;
        if (r?.data?.detail) {
          message = r.data.detail;
        }
      }
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <Container size="sm" py="xl">
        <Alert color="red" icon={<IconAlertCircle size={18} />}>
          Reset link is missing the token. Please use the link from the email
          you received, or request a new one.
        </Alert>
      </Container>
    );
  }

  return (
    <Box bg="gray.0" mih="100vh" w="100%">
      <Container size="sm" py="xl">
        <Card shadow="sm" padding="xl" radius="md" withBorder>
          <Stack gap="md">
            <Title order={2}>Set a new password</Title>
            {success ? (
              <Alert color="green" icon={<IconCircleCheck size={18} />}>
                Password updated. Redirecting to sign-in…
              </Alert>
            ) : (
              <form onSubmit={handleSubmit}>
                <Stack gap="sm">
                  <Text>Choose a new password for your account.</Text>
                  <PasswordInput
                    label="New password"
                    value={pw1}
                    onChange={(e) => setPw1(e.target.value)}
                    required
                    autoFocus
                  />
                  <PasswordInput
                    label="Confirm new password"
                    value={pw2}
                    onChange={(e) => setPw2(e.target.value)}
                    required
                  />
                  {error ? (
                    <Alert color="red" icon={<IconAlertCircle size={18} />}>
                      {error}
                    </Alert>
                  ) : null}
                  <Group justify="space-between" mt="xs">
                    <Anchor href="/forgot-password" size="sm" c="dark">
                      Request a new link
                    </Anchor>
                    <Button type="submit" loading={loading} color="dark">
                      Update password
                    </Button>
                  </Group>
                </Stack>
              </form>
            )}
          </Stack>
        </Card>
      </Container>
    </Box>
  );
}
