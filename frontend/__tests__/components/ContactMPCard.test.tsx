import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import ContactMPCard from "@/components/ContactMPCard";

const fullMP = {
  name: "YB Dato' Dr. Ramli bin Dato' Mohd Nor",
  photo_url: "https://parlimen.gov.my/images/P078.jpg",
  party: "BN",
  email: "ramli@parlimen.gov.my",
  phone: "03-2601 7222",
  facebook_url: "https://facebook.com/ramli",
  twitter_url: null,
  instagram_url: null,
  website_url: null,
  service_centre_address: "No 1, Jalan Meru, 31200 Ipoh, Perak",
  parlimen_profile_url: "https://www.parlimen.gov.my/profile-ahli.html?uweb=dr&id=4250",
  mymp_profile_url: "https://mymp.org.my/p/ramli-bin-dato-mohd-nor",
};

describe("ContactMPCard", () => {
  it("renders MP name and party", () => {
    render(<ContactMPCard mp={fullMP} constituencyCode="P078" constituencyName="Cameron Highlands" />);
    expect(screen.getByText(/Ramli/)).toBeInTheDocument();
    expect(screen.getByText(/BN/)).toBeInTheDocument();
  });

  it("renders email button with mailto link", () => {
    render(<ContactMPCard mp={fullMP} constituencyCode="P078" constituencyName="Cameron Highlands" />);
    const emailLink = screen.getByRole("link", { name: /email/i });
    expect(emailLink).toHaveAttribute("href", "mailto:ramli@parlimen.gov.my");
  });

  it("renders phone button with tel link", () => {
    render(<ContactMPCard mp={fullMP} constituencyCode="P078" constituencyName="Cameron Highlands" />);
    const phoneLink = screen.getByRole("link", { name: /call/i });
    expect(phoneLink).toHaveAttribute("href", "tel:03-2601 7222");
  });

  it("renders facebook button", () => {
    render(<ContactMPCard mp={fullMP} constituencyCode="P078" constituencyName="Cameron Highlands" />);
    const fbLink = screen.getByRole("link", { name: /facebook/i });
    expect(fbLink).toHaveAttribute("href", "https://facebook.com/ramli");
  });

  it("hides buttons when data is missing", () => {
    const minimalMP = { ...fullMP, email: null, phone: null, facebook_url: null };
    render(<ContactMPCard mp={minimalMP} constituencyCode="P078" constituencyName="Cameron Highlands" />);
    expect(screen.queryByRole("link", { name: /email/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /call/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /facebook/i })).not.toBeInTheDocument();
  });

  it("renders service centre address", () => {
    render(<ContactMPCard mp={fullMP} constituencyCode="P078" constituencyName="Cameron Highlands" />);
    expect(screen.getByText(/Jalan Meru/)).toBeInTheDocument();
  });

  it("renders external profile links", () => {
    render(<ContactMPCard mp={fullMP} constituencyCode="P078" constituencyName="Cameron Highlands" />);
    expect(screen.getByRole("link", { name: /parliament/i })).toHaveAttribute(
      "href",
      fullMP.parlimen_profile_url
    );
    expect(screen.getByRole("link", { name: /mymp/i })).toHaveAttribute(
      "href",
      fullMP.mymp_profile_url
    );
  });

  it("returns null when mp is null", () => {
    const { container } = render(
      <ContactMPCard mp={null} constituencyCode="P078" constituencyName="Cameron Highlands" />
    );
    expect(container.firstChild).toBeNull();
  });
});
