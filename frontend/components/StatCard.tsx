interface StatCardProps {
  label: string;
  value: string | number;
  icon?: string;
}

export default function StatCard({ label, value, icon }: StatCardProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 border-t-2 border-t-primary-500 p-4 text-center">
      {icon && <div className="text-2xl mb-1">{icon}</div>}
      <div className="text-2xl font-bold text-primary-700">
        {typeof value === "number" ? value.toLocaleString() : value}
      </div>
      <div className="text-sm text-gray-500 mt-1">{label}</div>
    </div>
  );
}
