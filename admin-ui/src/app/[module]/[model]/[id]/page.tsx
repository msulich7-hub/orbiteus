"use client";
import { use, useEffect, useState } from "react";
import { getCachedUiConfig, findModel, modelToFormStructure, type FormPanels } from "@/lib/modelConfig";
import ResourceForm, { type FieldDef } from "@/components/ResourceForm";
import ProspectConvertButton from "@/components/crm/ProspectConvertButton";
import LeadStageHistory from "@/components/crm/LeadStageHistory";
import { api } from "@/lib/api";
import { Group, Loader, Center, Paper, Stack, Text } from "@mantine/core";
import { humanizeRegistrySlugForUi } from "@/lib/formatters";

interface Params { module: string; model: string; id: string; }

const FALLBACK: FieldDef[] = [{ key: "name", label: "Name", type: "text", required: true }];

// Next 16 made route params async (see /[module]/[model]/page.tsx for details).
export default function DynamicEditPage({ params }: { params: Promise<Params> }) {
  const { module: mod, model, id } = use(params);
  const resource = `${mod}/${model}`;
  const title = humanizeRegistrySlugForUi(model);
  const [form, setForm] = useState<{ fields: FieldDef[]; panels?: FormPanels } | null>(null);
  const [isConverted, setIsConverted] = useState<boolean | null>(
    mod === "crm" && model === "prospect" ? null : false,
  );

  useEffect(() => {
    if (mod !== "crm" || model !== "prospect") return;
    let cancelled = false;
    api.get(`/crm/prospect/${id}`, { skipGlobalErrorToast: true })
      .then(({ data }) => {
        if (!cancelled) setIsConverted(Boolean(data.is_converted));
      })
      .catch(() => {
        if (!cancelled) setIsConverted(false);
      });
    return () => { cancelled = true; };
  }, [mod, model, id]);

  useEffect(() => {
    let cancelled = false;
    getCachedUiConfig()
      .then((cfg) => {
        if (cancelled) return;
        const m = findModel(cfg, mod, model);
        if (m && m.fields.length > 0) {
          setForm(modelToFormStructure(m));
        } else {
          setForm({ fields: FALLBACK });
        }
      })
      .catch(() => {
        if (!cancelled) setForm({ fields: FALLBACK });
      });
    return () => { cancelled = true; };
  }, [mod, model]);

  if (form === null) return <Center h={200}><Loader color="gray" size="sm" /></Center>;

  const showConvert =
    mod === "crm" && model === "prospect" && isConverted === false;

  return (
    <Stack gap="md">
      {showConvert && (
        <Paper p="md" withBorder>
          <Group justify="space-between" align="center" wrap="wrap">
            <Text size="sm" c="dimmed">
              Qualify this prospect and promote it to the sales pipeline.
            </Text>
            <ProspectConvertButton
              prospectId={id}
              isConverted={false}
              onConverted={() => setIsConverted(true)}
            />
          </Group>
        </Paper>
      )}
      <ResourceForm
        title={`Edit — ${title}`}
        resource={resource}
        recordId={id}
        fields={form.fields}
        panels={form.panels}
        backHref={`/${mod}/${model}`}
      />
      {mod === "crm" && model === "lead" && <LeadStageHistory leadId={id} />}
    </Stack>
  );
}
