import { LogOut, UserCircle } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function AccountSection() {
  const { session, signOut } = useAuth();
  const avatarUrl = session?.user.user_metadata?.avatar_url as string | undefined;
  const displayName = (session?.user.user_metadata?.full_name as string | undefined) ?? session?.user.email ?? "";
  const email = session?.user.email ?? "";

  return (
    <Card>
      <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
        <CardTitle className="text-base text-primary">Account</CardTitle>
      </CardHeader>
      <CardContent className="py-4 px-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {avatarUrl ? (
              <img src={avatarUrl} alt={displayName} className="h-14 w-14 rounded-full object-cover" />
            ) : (
              <div className="h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center">
                <UserCircle className="h-9 w-9 text-primary/60" />
              </div>
            )}
            <div>
              <div className="text-base font-semibold">{displayName}</div>
              <div className="text-sm text-muted-foreground">{email}</div>
            </div>
          </div>
          <Button variant="destructive" size="sm" onClick={signOut}>
            <LogOut className="h-4 w-4 mr-2" />
            Log out
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
