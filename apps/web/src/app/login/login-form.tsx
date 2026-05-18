"use client";

import { useActionState } from "react";
import { useSearchParams } from "next/navigation";
import { AlertCircleIcon, KeyRoundIcon, MailIcon } from "lucide-react";

import { authenticate } from "./actions";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { InputGroup, InputGroupAddon, InputGroupInput } from "@/components/ui/input-group";

export function LoginForm() {
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") || "/";
  const [errorMessage, formAction, isPending] = useActionState(authenticate, undefined);

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>HOU53</CardTitle>
        <CardDescription>Sign in with the configured demo user to estimate and save valuations.</CardDescription>
      </CardHeader>
      <CardContent>
        <form action={formAction} className="flex flex-col gap-5">
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="email">Email</FieldLabel>
              <InputGroup>
                <InputGroupAddon>
                  <MailIcon />
                </InputGroupAddon>
                <InputGroupInput id="email" name="email" type="email" autoComplete="email" required />
              </InputGroup>
            </Field>
            <Field>
              <FieldLabel htmlFor="password">Password</FieldLabel>
              <InputGroup>
                <InputGroupAddon>
                  <KeyRoundIcon />
                </InputGroupAddon>
                <InputGroupInput
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                />
              </InputGroup>
              <FieldDescription>Credentials are checked against environment configuration.</FieldDescription>
            </Field>
          </FieldGroup>
          <input type="hidden" name="redirectTo" value={callbackUrl} />
          {errorMessage ? (
            <Alert variant="destructive">
              <AlertCircleIcon />
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          ) : null}
          <Button type="submit" disabled={isPending}>
            {isPending ? "Signing in..." : "Sign in"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
