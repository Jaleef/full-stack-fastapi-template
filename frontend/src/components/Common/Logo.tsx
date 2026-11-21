import { Link } from "@tanstack/react-router"

import { cn } from "@/lib/utils"

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
}: LogoProps) {
  const content =
    variant === "responsive" ? (
      <>
        <span
          className={cn(
            "font-semibold tracking-tight group-data-[collapsible=icon]:hidden",
            className,
          )}
        >
          文档一致性分析
        </span>
        <span
          className={cn(
            "hidden font-semibold group-data-[collapsible=icon]:inline",
            className,
          )}
        >
          DC
        </span>
      </>
    ) : (
      <span className={cn("font-semibold tracking-tight", className)}>
        {variant === "full" ? "文档一致性分析" : "DC"}
      </span>
    )

  if (!asLink) {
    return content
  }

  return <Link to="/">{content}</Link>
}
