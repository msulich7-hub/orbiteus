"use client";

import { useState } from "react";
import { Button, FileInput, Group, Modal, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconDownload, IconUpload } from "@tabler/icons-react";

type CsvResource = "lead" | "prospect";

interface CrmCsvButtonsProps {
  resource: CsvResource;
}

export default function CrmCsvButtons({ resource }: CrmCsvButtonsProps) {
  const [importOpen, setImportOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleImport() {
    if (!importFile) {
      notifications.show({
        title: "No file selected",
        message: "Choose a CSV file to import.",
        color: "orange",
      });
      return;
    }

    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("file", importFile);

      const response = await fetch("/api/crm/prospect/import", {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(body?.detail?.message ?? body?.message ?? "Import failed");
      }

      notifications.show({
        title: "Import complete",
        message: `Imported ${body.imported ?? 0}, skipped ${body.skipped ?? 0}.`,
        color: "green",
      });
      setImportOpen(false);
      setImportFile(null);
      window.location.reload();
    } catch (error) {
      notifications.show({
        title: "Import failed",
        message: error instanceof Error ? error.message : "Could not import CSV.",
        color: "red",
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Group gap="xs">
        <Button
          component="a"
          href={`/api/crm/${resource}/export.csv`}
          download
          variant="default"
          size="sm"
          leftSection={<IconDownload size={16} />}
        >
          Export CSV
        </Button>
        {resource === "prospect" && (
          <Button
            variant="default"
            size="sm"
            leftSection={<IconUpload size={16} />}
            onClick={() => setImportOpen(true)}
          >
            Import CSV
          </Button>
        )}
      </Group>

      <Modal
        opened={importOpen}
        onClose={() => {
          if (!submitting) {
            setImportOpen(false);
            setImportFile(null);
          }
        }}
        title="Import prospects from CSV"
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Required column: name. Optional: organization_name, person_name, email, source,
            temperature, notes, utm_source, utm_campaign.
          </Text>
          <FileInput
            label="CSV file"
            accept=".csv"
            value={importFile}
            onChange={setImportFile}
            placeholder="Choose CSV"
          />
          <Group justify="flex-end">
            <Button
              variant="default"
              onClick={() => {
                setImportOpen(false);
                setImportFile(null);
              }}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button onClick={handleImport} loading={submitting}>
              Import
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
