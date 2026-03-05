interface StatCardProps {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  iconColor?: string;
}

export default function StatCard({ label, value, icon, iconColor = "text-amber-600" }: StatCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
      {icon && (
        <div className={`mb-2 ${iconColor}`}>
          {icon}
        </div>
      )}
      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</div>
      <div className="text-3xl font-bold text-gray-900 mt-1">
        {typeof value === "number" ? value.toLocaleString() : value}
      </div>
    </div>
  );
}
