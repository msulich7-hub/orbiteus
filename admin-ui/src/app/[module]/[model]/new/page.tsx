"use client";
import { use, useEffect, useState } from "react";
import { getCachedUiConfig, findModel, modelToFormStructure, type FormPanels } from "@/lib/modelConfig";
import ResourceForm, { type FieldDef } from "@/components/ResourceForm";
import { Loader, Center } from "@mantine/core";

interface Params { module: string; model: string; }

const FALLBACK: FieldDef[] = [{ key: "name", label: "Name", type: "text", required: true }];

// Next 16 made route params async (see /[module]/[model]/page.tsx for details).
export default function DynamicCreatePage({ params }: { params: Promise<Params> }) {
  const { module: mod, model } = use(params);
  const resource = `${mod}/${model}`;
  const title = model.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const [form, setForm] = useState<{ fields: FieldDef[]; panels?: FormPanels } | null>(null);

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

  return (
    <ResourceForm
      title={`New — ${title}`}
      resource={resource}
      fields={form.fields}
      panels={form.panels}
      backHref={`/${mod}/${model}`}
    />
  );
}
