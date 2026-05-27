"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Alert,
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Text,
} from "@mantine/core";
import { IconAlertCircle, IconArrowRight } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { api } from "@/lib/api";

interface Pipeline {
  id: string;
  name: string;
  is_default?: boolean;
}

interface Stage {
  id: string;
  name: string;
  pipeline_id: string;
  sequence: number;
  is_won?: boolean;
  is_lost?: boolean;
}

interface Props {
  prospectId: string;
  isConverted: boolean;
  onConverted?: () => void;
}

export default function ProspectConvertButton({
  prospectId,
  isConverted,
  onConverted,
}: Props) {
  const router = useRouter();
  const [opened, setOpened] = useState(false);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [stages, setStages] = useState<Stage[]>([]);
  const [pipelineId, setPipelineId] = useState<string | null>(null);
  const [stageId, setStageId] = useState<string | null>(null);
  const [expectedRevenue, setExpectedRevenue] = useState<number | string>(0);
  const [loadingOptions, setLoadingOptions] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const loadPipelines = useCallback(async () => {
    const { data } = await api.get("/crm/pipeline", { params: { limit: 50 } });
    const items: Pipeline[] = data.items ?? data ?? [];
    setPipelines(items);
    const fallback = items.find((p) => p.is_default)?.id ?? items[0]?.id ?? null;
    setPipelineId(fallback);
    return { items, fallback };
  }, []);

  const loadStages = useCallback(async (selectedPipelineId: string | null) => {
    if (!selectedPipelineId) {
      setStages([]);
      setStageId(null);
      return;
    }
    const { data } = await api.get("/crm/stage", { params: { limit: 200 } });
    const items: Stage[] = (data.items ?? data ?? []).filter(
      (s: Stage) =>
        s.pipeline_id === selectedPipelineId && !s.is_won && !s.is_lost,
    );
    items.sort((a, b) => a.sequence - b.sequence);
    setStages(items);
    setStageId(items[0]?.id ?? null);
  }, []);

  useEffect(() => {
    if (!opened) return;
    let cancelled = false;

    async function init() {
      setLoadingOptions(true);
      setError("");
      try {
        const { fallback } = await loadPipelines();
        if (!cancelled && fallback) {
          await loadStages(fallback);
        }
      } catch (e: unknown) {
        if (!cancelled) {
          setError((e as { message?: string }).message ?? "Failed to load pipelines");
        }
      } finally {
        if (!cancelled) setLoadingOptions(false);
      }
    }

    init();
    return () => {
      cancelled = true;
    };
  }, [opened, loadPipelines, loadStages]);

  async function onPipelineChange(value: string | null) {
    setPipelineId(value);
    setError("");
    try {
      await loadStages(value);
    } catch (e: unknown) {
      setError((e as { message?: string }).message ?? "Failed to load stages");
    }
  }

  function closeModal() {
    setOpened(false);
    setError("");
    setSubmitting(false);
  }

  async function handleConvert() {
    if (!pipelineId) {
      setError("Select a pipeline");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      const body: {
        pipeline_id: string;
        stage_id?: string;
        expected_revenue?: number;
      } = { pipeline_id: pipelineId };

      if (stageId) body.stage_id = stageId;
      const revenue = Number(expectedRevenue);
      if (!Number.isNaN(revenue) && revenue > 0) {
        body.expected_revenue = revenue;
      }

      const { data } = await api.post<{ lead_id: string }>(
        `/crm/prospect/${prospectId}/convert`,
        body,
        { skipGlobalErrorToast: true },
      );

      notifications.show({
        title: "Converted",
        message: "Prospect is now a pipeline deal.",
        color: "green",
      });

      onConverted?.();
      closeModal();
      router.push(`/crm/lead/${data.lead_id}`);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(err.response?.data?.detail ?? err.message ?? "Conversion failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (isConverted) return null;

  return (
    <>
      <Button
        leftSection={<IconArrowRight size={16} />}
        onClick={() => setOpened(true)}
      >
        Convert to deal
      </Button>

      <Modal
        opened={opened}
        onClose={closeModal}
        title="Convert prospect to deal"
        size="md"
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Choose a pipeline and optional stage. A new deal will be created from this prospect.
          </Text>

          {error && (
            <Alert icon={<IconAlertCircle size={16} />} color="red">
              {error}
            </Alert>
          )}

          <Select
            label="Pipeline"
            placeholder="Select pipeline"
            data={pipelines.map((p) => ({ value: p.id, label: p.name }))}
            value={pipelineId}
            onChange={onPipelineChange}
            disabled={loadingOptions || submitting}
            required
            allowDeselect={false}
          />

          <Select
            label="Stage"
            description="Optional — first open stage is used if empty"
            placeholder={stages.length ? "Select stage" : "No stages for pipeline"}
            data={stages.map((s) => ({ value: s.id, label: s.name }))}
            value={stageId}
            onChange={setStageId}
            disabled={loadingOptions || submitting || stages.length === 0}
            clearable
          />

          <NumberInput
            label="Expected revenue"
            description="Optional deal value"
            value={expectedRevenue}
            onChange={setExpectedRevenue}
            min={0}
            decimalScale={2}
            fixedDecimalScale
            disabled={submitting}
          />

          <Group justify="flex-end" mt="xs">
            <Button variant="default" onClick={closeModal} disabled={submitting}>
              Cancel
            </Button>
            <Button
              leftSection={<IconArrowRight size={16} />}
              loading={submitting}
              onClick={handleConvert}
            >
              Convert
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
