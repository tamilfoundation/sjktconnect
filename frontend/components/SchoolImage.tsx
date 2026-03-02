"use client";

import { useState } from "react";
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
  let photoList: SchoolImageData[];
  if (images && images.length > 0) {
    photoList = images;
  } else if (imageUrl) {
    photoList = [{ image_url: imageUrl, source: "PLACES" as const, is_primary: true, attribution: "" }];
  } else {
    photoList = [];
  }

  const [activeIndex, setActiveIndex] = useState(0);

  if (photoList.length === 0) {
    return (
      <div className="mb-6 bg-gray-100 rounded-lg h-48 flex items-center justify-center">
        <p className="text-gray-400 text-sm">
          No photo available. Know this school? Help us by sharing a photo.
        </p>
      </div>
    );
  }

  const active = photoList[activeIndex];

  return (
    <div className="mb-6">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={active.image_url}
        alt={schoolName}
        className="w-full h-48 sm:h-64 object-cover rounded-lg"
        loading="lazy"
      />
      {active.attribution && (
        <p className="text-xs text-gray-400 mt-1">
          Photo: {active.attribution.replace(/<[^>]*>/g, "")}
        </p>
      )}
      {photoList.length > 1 && (
        <div className="flex gap-2 mt-2">
          {photoList.map((img, i) => i !== activeIndex && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              key={i}
              src={img.image_url}
              alt={`${schoolName} photo ${i + 1}`}
              className="w-20 h-14 object-cover rounded border border-gray-200 cursor-pointer hover:border-blue-400 transition-colors"
              loading="lazy"
              onClick={() => setActiveIndex(i)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
