import { SchoolImageData } from "@/lib/types";

interface Props {
  images?: SchoolImageData[];
  schoolName: string;
  imageUrl?: string | null;
}

export default function SchoolPhotoGallery({
  images,
  schoolName,
  imageUrl,
}: Props) {
  // Use images array if available, fall back to single imageUrl
  const photoList: SchoolImageData[] =
    images && images.length > 0
      ? images
      : imageUrl
        ? [{ image_url: imageUrl, source: "PLACES" as const, is_primary: true, attribution: "" }]
        : [];

  if (photoList.length === 0) {
    return (
      <div className="mb-6 bg-gray-100 rounded-lg h-48 flex items-center justify-center">
        <p className="text-gray-400 text-sm">
          No photo available. Know this school? Help us by sharing a photo.
        </p>
      </div>
    );
  }

  const primary = photoList.find((img) => img.is_primary) || photoList[0];
  const thumbnails = photoList.filter((img) => img !== primary);

  return (
    <div className="mb-6">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={primary.image_url}
        alt={schoolName}
        className="w-full h-48 sm:h-64 object-cover rounded-lg"
        loading="lazy"
      />
      {primary.attribution && (
        <p className="text-xs text-gray-400 mt-1">
          Photo: {primary.attribution.replace(/<[^>]*>/g, "")}
        </p>
      )}
      {thumbnails.length > 0 && (
        <div className="flex gap-2 mt-2">
          {thumbnails.map((img, i) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              key={i}
              src={img.image_url}
              alt={`${schoolName} photo ${i + 2}`}
              className="w-20 h-14 object-cover rounded border border-gray-200"
              loading="lazy"
            />
          ))}
        </div>
      )}
    </div>
  );
}
