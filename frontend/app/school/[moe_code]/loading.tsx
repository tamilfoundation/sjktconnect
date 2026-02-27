export default function SchoolLoading() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 animate-pulse">
      {/* Breadcrumb skeleton */}
      <div className="h-4 bg-gray-200 rounded w-48 mb-4" />

      {/* Title skeleton */}
      <div className="mb-6">
        <div className="h-8 bg-gray-200 rounded w-80 mb-2" />
        <div className="h-4 bg-gray-200 rounded w-48" />
      </div>

      {/* Claim button skeleton */}
      <div className="h-32 bg-gray-100 rounded-lg mb-6" />

      {/* Content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Stats skeleton */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-20 bg-gray-100 rounded-lg border border-gray-200"
              />
            ))}
          </div>

          {/* Details skeleton */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="h-6 bg-gray-200 rounded w-40 mb-4" />
            <div className="space-y-3">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="h-4 bg-gray-100 rounded w-full" />
              ))}
            </div>
          </div>

          {/* Map skeleton */}
          <div className="h-64 bg-gray-100 rounded-lg border border-gray-200" />
        </div>

        {/* Sidebar skeleton */}
        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="h-6 bg-gray-200 rounded w-48 mb-3" />
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-4 bg-gray-100 rounded w-full" />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
