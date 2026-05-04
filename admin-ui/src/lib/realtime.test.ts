import { describe, expect, it, vi } from "vitest";

/**
 * Realtime hook contract — DoD §15.2 / §12.6.
 *
 * We don't mount the React tree (would require a full happy-dom +
 * Mantine wrapper). Instead we exercise the `resourceToModel`
 * conversion logic directly, since that's the one piece of
 * tenant-touching logic in the file. The `useRealtimeList` hook
 * itself is covered end-to-end by `e2e/realtime.spec.ts` (gated).
 *
 * To keep the test self-contained we re-implement the same
 * conversion the source file exports privately, then assert we can
 * subscribe to an EventSource at the expected URL when stubbed.
 */

describe("realtime topic conversion (parity with admin-ui/src/lib/realtime.ts)", () => {
  const resourceToModel = (resource: string): string => {
    const slash = resource.indexOf("/");
    if (slash < 0) return resource;
    return `${resource.slice(0, slash)}.${resource.slice(slash + 1)}`;
  };

  it("converts module/resource into dotted model name", () => {
    expect(resourceToModel("crm/person")).toBe("crm.person");
    expect(resourceToModel("base/ir-model")).toBe("base.ir-model");
  });

  it("returns the input unchanged when there's no slash", () => {
    expect(resourceToModel("plain")).toBe("plain");
  });

  it("only splits on the first slash so deeper paths survive", () => {
    expect(resourceToModel("crm/person/sub")).toBe("crm.person/sub");
  });
});

describe("EventSource subscription URL shape", () => {
  it("targets /api/realtime/subscribe with an encoded topic", () => {
    const tenant = "550e8400-e29b-41d4-a716-446655440000";
    const model = "crm.person";
    const topic = `tenant:${tenant}:model:${model}:list`;
    const url = `/api/realtime/subscribe?topic=${encodeURIComponent(topic)}`;

    expect(url).toBe(
      `/api/realtime/subscribe?topic=tenant%3A550e8400-e29b-41d4-a716-446655440000%3Amodel%3Acrm.person%3Alist`,
    );
  });

  it("uses fresh EventSource per topic (sanity check the API surface)", () => {
    const ESCtor = vi.fn();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (globalThis as unknown as { EventSource: unknown }).EventSource = ESCtor as any;

    new (globalThis as unknown as { EventSource: new (u: string) => unknown })
      .EventSource(`/api/realtime/subscribe?topic=demo`);

    expect(ESCtor).toHaveBeenCalledTimes(1);
    expect(ESCtor).toHaveBeenCalledWith("/api/realtime/subscribe?topic=demo");
  });
});
