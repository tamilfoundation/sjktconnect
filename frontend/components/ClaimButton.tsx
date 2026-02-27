interface ClaimButtonProps {
  moeCode: string;
}

export default function ClaimButton({ moeCode }: ClaimButtonProps) {
  return (
    <div className="bg-gradient-to-r from-primary-50 to-primary-100 border border-primary-200 rounded-lg p-6 text-center">
      <h3 className="text-lg font-semibold text-primary-800 mb-2">
        Are you from this school?
      </h3>
      <p className="text-sm text-primary-700 mb-4">
        Verify and update your school&apos;s information to keep it accurate.
      </p>
      <button
        className="inline-block bg-primary-600 text-white font-medium px-6 py-3 rounded-lg hover:bg-primary-700 transition-colors"
        title={`Claim school ${moeCode}`}
        disabled
      >
        Claim This Page
      </button>
      <p className="text-xs text-primary-500 mt-2">
        Coming soon — requires a valid @moe.edu.my email address
      </p>
    </div>
  );
}
