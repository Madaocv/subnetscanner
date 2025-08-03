import SitesList from '@/components/SitesList';

export default function SitesPage() {
  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Sites</h1>
      </div>
      <SitesList />
    </div>
  );
}
