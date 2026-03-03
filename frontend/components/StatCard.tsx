interface StatCardProps {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  iconColor?: string;
}

export default function StatCard({ label, value, icon, iconColor = "text-primary-600" }: StatCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 flex flex-col items-center justify-center text-center">
      {icon && (
        <div className={`mb-1 ${iconColor}`}>
          {icon}
        </div>
      )}
      <div className="text-2xl font-bold text-gray-900">
        {typeof value === "number" ? value.toLocaleString() : value}
      </div>
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mt-1">{label}</div>
    </div>
  );
}
