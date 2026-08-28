import { EcgChart } from "@/components/EcgChart";
import { DfaChart } from "@/components/DfaChart";
import { Timer, Heart, Activity } from "lucide-react";

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-50">
          Session Dashboard
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Real-time biometric monitoring and aerobic threshold (Zone 2) tracking.
        </p>
      </header>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Card 1 */}
        <div className="bg-white dark:bg-gray-900 overflow-hidden rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm p-5">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Timer className="h-6 w-6 text-blue-600 dark:text-blue-400" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Duration</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100" aria-label="Session duration: 45 minutes and 12 seconds">
                45:12
              </p>
            </div>
          </div>
        </div>

        {/* Card 2 */}
        <div className="bg-white dark:bg-gray-900 overflow-hidden rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm p-5">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
              <Heart className="h-6 w-6 text-red-600 dark:text-red-400" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Heart Rate</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100" aria-label="Current heart rate: 132 beats per minute">
                132 <span className="text-sm font-normal text-gray-500">BPM</span>
              </p>
            </div>
          </div>
        </div>

        {/* Card 3 */}
        <div className="bg-white dark:bg-gray-900 overflow-hidden rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm p-5 sm:col-span-2 lg:col-span-1">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg">
              <Activity className="h-6 w-6 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Current Zone</p>
              <div className="flex items-center gap-2">
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  Zone 2
                </p>
                <span className="inline-flex items-center rounded-full bg-emerald-100 dark:bg-emerald-900/30 px-2.5 py-0.5 text-xs font-medium text-emerald-800 dark:text-emerald-300">
                  Optimal
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 mt-8">
        <div className="h-[350px]">
          <EcgChart />
        </div>
        <div className="h-[350px]">
          <DfaChart />
        </div>
      </div>
    </div>
  );
}
