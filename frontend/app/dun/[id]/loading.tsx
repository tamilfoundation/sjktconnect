export default function DUNLoading() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-72 mb-4" />
      <div className="h-8 bg-gray-200 rounded w-64 mb-2" />
      <div className="h-4 bg-gray-200 rounded w-48 mb-6" />
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 bg-gray-100 rounded-lg border border-gray-200" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="h-72 bg-gray-100 rounded-lg border border-gray-200" />
          <div className="h-48 bg-gray-100 rounded-lg border border-gray-200" />
        </div>
        <div className="h-40 bg-gray-100 rounded-lg border border-gray-200" />
      </div>
    </div>
  );
}
