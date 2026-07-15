import type { ReactNode } from "react";

type KpiCardProps = {
  title: string;
  value: string | number;
  subtitle: string;
  icon?: ReactNode;
};

export default function KpiCard({ title, value, subtitle, icon }: KpiCardProps) {
  return (
    <div className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
      <div className="flex items-center justify-between">
        <div className="h-12 w-12 rounded-2xl bg-emerald-100 flex items-center justify-center text-emerald-600">
          {icon}
        </div>
      </div>

      <p className="mt-6 text-sm font-medium text-gray-600">{title}</p>
      <h2 className="mt-2 text-4xl font-bold text-gray-900">{value}</h2>
      <p className="mt-2 text-sm text-gray-500">{subtitle}</p>
    </div>
  );
}
