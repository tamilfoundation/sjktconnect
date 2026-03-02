import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import UnsubscribeConfirmation from "@/components/UnsubscribeConfirmation";
import Breadcrumb from "@/components/Breadcrumb";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("subscribe");
  return {
    title: `${t("unsubscribeTitle")} | SJK(T) Connect`,
    description: t("unsubscribeTitle"),
  };
}

interface UnsubscribePageProps {
  params: Promise<{ token: string }>;
}

export default async function UnsubscribePage({ params }: UnsubscribePageProps) {
  const { token } = await params;
  const t = await getTranslations("subscribe");
  const tc = await getTranslations("common");

  return (
    <main className="max-w-lg mx-auto px-4 py-8">
      <Breadcrumb
        items={[
          { label: tc("home"), href: "/" },
          { label: t("unsubscribeTitle") },
        ]}
      />

      <div className="mt-6 bg-white rounded-lg shadow-sm border p-6">
        <UnsubscribeConfirmation token={token} />
      </div>
    </main>
  );
}
