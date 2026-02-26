export default function Footer() {
  return (
    <footer className="bg-white border-t border-gray-200 py-4">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <p className="text-center text-xs text-gray-500">
          &copy; {new Date().getFullYear()} Tamil Foundation Malaysia.
          Data from MOE &amp; Parliament of Malaysia.
        </p>
      </div>
    </footer>
  );
}
