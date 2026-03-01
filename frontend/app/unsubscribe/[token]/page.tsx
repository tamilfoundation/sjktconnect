import { Metadata } from "next";
import UnsubscribeConfirmation from "@/components/UnsubscribeConfirmation";
import Breadcrumb from "@/components/Breadcrumb";

export const metadata: Metadata = {
  title: "Unsubscribe | SJK(T) Connect",
  description: "Unsubscribe from SJK(T) Connect communications.",
};

interface UnsubscribePageProps {
  params: Promise<{ token: string }>;
}

export default async function UnsubscribePage({ params }: UnsubscribePageProps) {
  const { token } = await params;

  return (
    <main className="max-w-lg mx-auto px-4 py-8">
      <Breadcrumb
        items={[
          { label: "Home", href: "/" },
          { label: "Unsubscribe" },
        ]}
      />

      <div className="mt-6 bg-white rounded-lg shadow-sm border p-6">
        <UnsubscribeConfirmation token={token} />
      </div>
    </main>
  );
}
