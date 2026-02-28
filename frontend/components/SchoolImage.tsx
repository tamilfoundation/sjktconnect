interface SchoolImageProps {
  imageUrl: string;
  schoolName: string;
}

export default function SchoolImage({ imageUrl, schoolName }: SchoolImageProps) {
  return (
    <div className="mb-6 rounded-lg overflow-hidden border border-gray-200">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={imageUrl}
        alt={schoolName}
        className="w-full h-48 sm:h-64 object-cover"
        loading="lazy"
      />
    </div>
  );
}
