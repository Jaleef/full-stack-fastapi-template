import { createFileRoute } from "@tanstack/react-router"

export const Route = createFileRoute("/_layout/analysis/$analysisId")({
  component: AnalysisPage,
  head: () => ({
    meta: [{ title: "分析结果" }],
  }),
})

function AnalysisPage() {
  // TODO(H5-H7): overview, findings, mapping and audit tabs.
  return null
}
