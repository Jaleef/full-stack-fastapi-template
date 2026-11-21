interface ParseConfirmProps {
  analysis: unknown
  onStart?: () => void
  onReconfigure?: (config: Record<string, string>) => void
}

export function ParseConfirm(_props: ParseConfirmProps) {
  // TODO(H2): show block stats, warnings and extraction source selectors.
  return null
}
