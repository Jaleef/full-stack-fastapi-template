import { createFileRoute } from "@tanstack/react-router"

export const Route = createFileRoute("/_layout/")({
  component: WorkspacePage,
  head: () => ({
    meta: [{ title: "一致性分析" }],
  }),
})

function WorkspacePage() {
  // TODO(H4): upload panel, parse confirmation and analysis history.
  return null
}
