export default function SchoolHistory() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-3">
        History &amp; Story
      </h2>
      <p className="text-sm text-gray-500 mb-4">
        Every Tamil school has a story worth telling. Help us preserve it.
      </p>
      <p className="text-sm text-gray-600">
        If you have information about this school&rsquo;s history &mdash;
        founding year, key milestones, notable alumni &mdash; we&rsquo;d
        love to hear from you.
      </p>
      <a
        href="mailto:info@tamilfoundation.org?subject=School%20History%20Contribution"
        className="inline-block mt-4 text-sm font-medium text-primary-600 hover:text-primary-800"
      >
        Contact us to contribute &rarr;
      </a>
    </div>
  );
}
