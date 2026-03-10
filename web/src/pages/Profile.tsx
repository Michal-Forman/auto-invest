import { useState } from "react";
import { Eye, EyeOff, UserCircle } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useProfile } from "@/hooks/use-profile";
import { useConfig } from "@/hooks/use-config";
import { usePageTitle } from "@/hooks/use-page-title";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { CapType, UserProfile } from "@/types";

const capVariants: Record<CapType, string> = {
  none: "bg-gray-100 text-gray-700 border-gray-200",
  soft: "bg-blue-100 text-blue-700 border-blue-200",
  hard: "bg-purple-100 text-purple-700 border-purple-200",
};

function SecretInput({
  id,
  value,
  onChange,
  placeholder,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <Input
        id={id}
        type={show ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="pr-9"
      />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
      >
        {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}

function CardSaveButton({ onClick, disabled }: { onClick: () => void; disabled?: boolean }) {
  return (
    <Button size="sm" onClick={onClick} disabled={disabled} className="mt-4">
      Save
    </Button>
  );
}

export function Profile() {
  usePageTitle("Profile");
  const { session } = useAuth();
  const { data: profile, loading, error, updateProfile, updating } = useProfile();
  const { data: config } = useConfig();

  const avatarUrl = session?.user.user_metadata?.avatar_url as string | undefined;
  const displayName = (session?.user.user_metadata?.full_name as string | undefined) ?? session?.user.email ?? "";
  const email = session?.user.email ?? "";

  // T212 form state
  const [t212, setT212] = useState<{ t212_id_key: string; t212_private_key: string; pie_id: string }>({
    t212_id_key: "",
    t212_private_key: "",
    pie_id: "",
  });
  const [t212Ready, setT212Ready] = useState(false);

  // Coinmate form state
  const [coinmate, setCoinmate] = useState<{
    coinmate_client_id: string;
    coinmate_public_key: string;
    coinmate_private_key: string;
  }>({ coinmate_client_id: "", coinmate_public_key: "", coinmate_private_key: "" });
  const [coinmateReady, setCoinmateReady] = useState(false);

  // Portfolio form state
  const [portfolio, setPortfolio] = useState<{
    invest_amount: string;
    t212_weight: string;
    btc_weight: string;
    invest_interval: string;
    balance_buffer: string;
    balance_alert_days: string;
    btc_withdrawal_treshold: string;
    btc_external_adress: string;
  }>({
    invest_amount: "",
    t212_weight: "",
    btc_weight: "",
    invest_interval: "",
    balance_buffer: "",
    balance_alert_days: "",
    btc_withdrawal_treshold: "",
    btc_external_adress: "",
  });
  const [portfolioReady, setPortfolioReady] = useState(false);

  // Mail form state
  const [mail, setMail] = useState<{
    mail_host: string;
    mail_port: string;
    mail_password: string;
    my_mail: string;
    mail_recipient: string;
  }>({ mail_host: "", mail_port: "", mail_password: "", my_mail: "", mail_recipient: "" });
  const [mailReady, setMailReady] = useState(false);

  // Deposit form state
  const [deposit, setDeposit] = useState<{
    t212_deposit_account: string;
    t212_deposit_vs: string;
    coinmate_deposit_account: string;
    coinmate_deposit_vs: string;
  }>({
    t212_deposit_account: "",
    t212_deposit_vs: "",
    coinmate_deposit_account: "",
    coinmate_deposit_vs: "",
  });
  const [depositReady, setDepositReady] = useState(false);

  // Initialize form state from profile on first load
  if (profile && !t212Ready) {
    setT212({
      t212_id_key: profile.t212_id_key,
      t212_private_key: profile.t212_private_key,
      pie_id: profile.pie_id != null ? String(profile.pie_id) : "",
    });
    setT212Ready(true);
  }
  if (profile && !coinmateReady) {
    setCoinmate({
      coinmate_client_id: profile.coinmate_client_id != null ? String(profile.coinmate_client_id) : "",
      coinmate_public_key: profile.coinmate_public_key,
      coinmate_private_key: profile.coinmate_private_key,
    });
    setCoinmateReady(true);
  }
  if (profile && !portfolioReady) {
    setPortfolio({
      invest_amount: String(profile.invest_amount),
      t212_weight: String(profile.t212_weight),
      btc_weight: String(profile.btc_weight),
      invest_interval: profile.invest_interval,
      balance_buffer: String(profile.balance_buffer),
      balance_alert_days: String(profile.balance_alert_days),
      btc_withdrawal_treshold: String(profile.btc_withdrawal_treshold),
      btc_external_adress: profile.btc_external_adress,
    });
    setPortfolioReady(true);
  }
  if (profile && !mailReady) {
    setMail({
      mail_host: profile.mail_host,
      mail_port: String(profile.mail_port),
      mail_password: profile.mail_password,
      my_mail: profile.my_mail,
      mail_recipient: profile.mail_recipient,
    });
    setMailReady(true);
  }
  if (profile && !depositReady) {
    setDeposit({
      t212_deposit_account: profile.t212_deposit_account ?? "",
      t212_deposit_vs: profile.t212_deposit_vs ?? "",
      coinmate_deposit_account: profile.coinmate_deposit_account ?? "",
      coinmate_deposit_vs: profile.coinmate_deposit_vs ?? "",
    });
    setDepositReady(true);
  }

  const saveT212 = () =>
    updateProfile({
      t212_id_key: t212.t212_id_key,
      t212_private_key: t212.t212_private_key,
      pie_id: t212.pie_id !== "" ? Number(t212.pie_id) : null,
    } as Partial<UserProfile>);

  const saveCoinmate = () =>
    updateProfile({
      coinmate_client_id: coinmate.coinmate_client_id !== "" ? Number(coinmate.coinmate_client_id) : null,
      coinmate_public_key: coinmate.coinmate_public_key,
      coinmate_private_key: coinmate.coinmate_private_key,
    } as Partial<UserProfile>);

  const savePortfolio = () =>
    updateProfile({
      invest_amount: Number(portfolio.invest_amount),
      t212_weight: Number(portfolio.t212_weight),
      btc_weight: Number(portfolio.btc_weight),
      invest_interval: portfolio.invest_interval,
      balance_buffer: Number(portfolio.balance_buffer),
      balance_alert_days: Number(portfolio.balance_alert_days),
      btc_withdrawal_treshold: Number(portfolio.btc_withdrawal_treshold),
      btc_external_adress: portfolio.btc_external_adress,
    });

  const saveMail = () =>
    updateProfile({
      mail_host: mail.mail_host,
      mail_port: Number(mail.mail_port),
      mail_password: mail.mail_password,
      my_mail: mail.my_mail,
      mail_recipient: mail.mail_recipient,
    });

  const saveDeposit = () =>
    updateProfile({
      t212_deposit_account: deposit.t212_deposit_account || null,
      t212_deposit_vs: deposit.t212_deposit_vs || null,
      coinmate_deposit_account: deposit.coinmate_deposit_account || null,
      coinmate_deposit_vs: deposit.coinmate_deposit_vs || null,
    } as Partial<UserProfile>);

  if (loading) return <p className="text-muted-foreground p-6">Loading…</p>;
  if (error || !profile) return <p className="text-red-600 p-6">Failed to load profile.</p>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-primary">Profile</h1>

      {/* Identity card */}
      <Card>
        <CardContent className="pt-6">
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
        </CardContent>
      </Card>

      {/* Trading 212 */}
      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <CardTitle className="text-base text-primary">Trading 212</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 pt-4">
          <Field label="API ID Key">
            <SecretInput
              id="t212_id_key"
              value={t212.t212_id_key}
              onChange={(v) => setT212((s) => ({ ...s, t212_id_key: v }))}
              placeholder="t212_id_key"
            />
          </Field>
          <Field label="Private Key">
            <SecretInput
              id="t212_private_key"
              value={t212.t212_private_key}
              onChange={(v) => setT212((s) => ({ ...s, t212_private_key: v }))}
              placeholder="t212_private_key"
            />
          </Field>
          <Field label="Pie ID (optional)">
            <Input
              id="pie_id"
              value={t212.pie_id}
              onChange={(e) => setT212((s) => ({ ...s, pie_id: e.target.value }))}
              placeholder="123456"
            />
          </Field>
          <CardSaveButton onClick={saveT212} disabled={updating} />
        </CardContent>
      </Card>

      {/* Coinmate */}
      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <CardTitle className="text-base text-primary">Coinmate</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 pt-4">
          <Field label="Client ID">
            <Input
              id="coinmate_client_id"
              value={coinmate.coinmate_client_id}
              onChange={(e) => setCoinmate((s) => ({ ...s, coinmate_client_id: e.target.value }))}
              placeholder="12345"
            />
          </Field>
          <Field label="Public Key">
            <Input
              id="coinmate_public_key"
              value={coinmate.coinmate_public_key}
              onChange={(e) => setCoinmate((s) => ({ ...s, coinmate_public_key: e.target.value }))}
            />
          </Field>
          <Field label="Private Key">
            <SecretInput
              id="coinmate_private_key"
              value={coinmate.coinmate_private_key}
              onChange={(v) => setCoinmate((s) => ({ ...s, coinmate_private_key: v }))}
            />
          </Field>
          <CardSaveButton onClick={saveCoinmate} disabled={updating} />
        </CardContent>
      </Card>

      {/* Portfolio */}
      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <CardTitle className="text-base text-primary">Portfolio</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 pt-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Invest Amount (CZK)">
              <Input
                value={portfolio.invest_amount}
                onChange={(e) => setPortfolio((s) => ({ ...s, invest_amount: e.target.value }))}
              />
            </Field>
            <Field label="T212 Weight">
              <Input
                value={portfolio.t212_weight}
                onChange={(e) => setPortfolio((s) => ({ ...s, t212_weight: e.target.value }))}
              />
            </Field>
            <Field label="BTC Weight">
              <Input
                value={portfolio.btc_weight}
                onChange={(e) => setPortfolio((s) => ({ ...s, btc_weight: e.target.value }))}
              />
            </Field>
            <Field label="Invest Interval (cron)">
              <Input
                value={portfolio.invest_interval}
                onChange={(e) => setPortfolio((s) => ({ ...s, invest_interval: e.target.value }))}
                placeholder="0 9 1 * *"
              />
            </Field>
            <Field label="Balance Buffer (CZK)">
              <Input
                value={portfolio.balance_buffer}
                onChange={(e) => setPortfolio((s) => ({ ...s, balance_buffer: e.target.value }))}
              />
            </Field>
            <Field label="Balance Alert Days">
              <Input
                value={portfolio.balance_alert_days}
                onChange={(e) => setPortfolio((s) => ({ ...s, balance_alert_days: e.target.value }))}
              />
            </Field>
            <Field label="BTC Withdrawal Threshold (sats)">
              <Input
                value={portfolio.btc_withdrawal_treshold}
                onChange={(e) => setPortfolio((s) => ({ ...s, btc_withdrawal_treshold: e.target.value }))}
              />
            </Field>
            <Field label="BTC External Address">
              <Input
                value={portfolio.btc_external_adress}
                onChange={(e) => setPortfolio((s) => ({ ...s, btc_external_adress: e.target.value }))}
                placeholder="bc1q..."
              />
            </Field>
          </div>
          <CardSaveButton onClick={savePortfolio} disabled={updating} />
        </CardContent>
      </Card>

      {/* Email Notifications */}
      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <CardTitle className="text-base text-primary">Email Notifications</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 pt-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Mail Host">
              <Input
                value={mail.mail_host}
                onChange={(e) => setMail((s) => ({ ...s, mail_host: e.target.value }))}
                placeholder="smtp.example.com"
              />
            </Field>
            <Field label="Mail Port">
              <Input
                value={mail.mail_port}
                onChange={(e) => setMail((s) => ({ ...s, mail_port: e.target.value }))}
                placeholder="465"
              />
            </Field>
            <Field label="Mail Password">
              <SecretInput
                id="mail_password"
                value={mail.mail_password}
                onChange={(v) => setMail((s) => ({ ...s, mail_password: v }))}
              />
            </Field>
            <Field label="From Address">
              <Input
                value={mail.my_mail}
                onChange={(e) => setMail((s) => ({ ...s, my_mail: e.target.value }))}
                placeholder="me@example.com"
              />
            </Field>
            <Field label="Recipient">
              <Input
                value={mail.mail_recipient}
                onChange={(e) => setMail((s) => ({ ...s, mail_recipient: e.target.value }))}
                placeholder="you@example.com"
              />
            </Field>
          </div>
          <CardSaveButton onClick={saveMail} disabled={updating} />
        </CardContent>
      </Card>

      {/* Deposit Info */}
      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <CardTitle className="text-base text-primary">Deposit Info</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 pt-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="T212 Deposit Account">
              <Input
                value={deposit.t212_deposit_account}
                onChange={(e) => setDeposit((s) => ({ ...s, t212_deposit_account: e.target.value }))}
              />
            </Field>
            <Field label="T212 Deposit VS">
              <Input
                value={deposit.t212_deposit_vs}
                onChange={(e) => setDeposit((s) => ({ ...s, t212_deposit_vs: e.target.value }))}
              />
            </Field>
            <Field label="Coinmate Deposit Account">
              <Input
                value={deposit.coinmate_deposit_account}
                onChange={(e) => setDeposit((s) => ({ ...s, coinmate_deposit_account: e.target.value }))}
              />
            </Field>
            <Field label="Coinmate Deposit VS">
              <Input
                value={deposit.coinmate_deposit_vs}
                onChange={(e) => setDeposit((s) => ({ ...s, coinmate_deposit_vs: e.target.value }))}
              />
            </Field>
          </div>
          <CardSaveButton onClick={saveDeposit} disabled={updating} />
        </CardContent>
      </Card>

      {/* Cron Control */}
      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <CardTitle className="text-base text-primary">Automation</CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <Switch
              id="cron_enabled"
              checked={profile.cron_enabled}
              onCheckedChange={(checked) => updateProfile({ cron_enabled: checked })}
              disabled={updating}
            />
            <Label htmlFor="cron_enabled" className="text-sm">
              Enable scheduled investing (cron)
            </Label>
          </div>
        </CardContent>
      </Card>

      {/* Instrument Registry (read-only) */}
      {config && (
        <Card>
          <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
            <CardTitle className="text-base text-primary">Instrument Registry</CardTitle>
          </CardHeader>
          <CardContent className="p-0 -mt-4">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 hover:bg-muted/40">
                  <TableHead>Ticker</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Currency</TableHead>
                  <TableHead>Cap Type</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {config.instruments.map((inst) => (
                  <TableRow key={inst.ticker}>
                    <TableCell className="font-mono text-sm font-medium">{inst.ticker}</TableCell>
                    <TableCell>{inst.display_name}</TableCell>
                    <TableCell>{inst.instrument_type}</TableCell>
                    <TableCell>{inst.currency}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={capVariants[inst.cap_type]}>
                        {inst.cap_type}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
