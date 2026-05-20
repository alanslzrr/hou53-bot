"use client";

import { CircleHelpIcon } from "lucide-react";

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

type InfoTooltipProps = {
  label: string;
  children: string;
  className?: string;
};

export function InfoTooltip({ label, children, className }: InfoTooltipProps) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            aria-label={label}
            className={cn(
              "inline-flex size-4 shrink-0 cursor-help items-center justify-center rounded-full text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              className,
            )}
            role="button"
            tabIndex={0}
          >
            <CircleHelpIcon className="size-3.5" />
          </span>
        </TooltipTrigger>
        <TooltipContent side="top" sideOffset={6}>
          {children}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
