export type DashboardModuleKey =
  | 'dispense'
  | 'medicineInfo'
  | 'reports'
  | 'patients'
  | 'medicineLocations'
  | 'medicineSettings'
  | 'writeoff'
  | 'operationLog'
  | 'medicineDown'
  | 'restock'
  | 'inventory'
  | 'prescriptions';

export interface DashboardModule {
  key: DashboardModuleKey;
  to: string | null;
  label: string;
  available: boolean;
}

export const DASHBOARD_MODULES: DashboardModule[] = [
  { key: 'dispense', to: '/dispense', label: '医嘱取药', available: false },
  { key: 'medicineInfo', to: '/medicine-info', label: '药盒信息', available: true },
  { key: 'reports', to: '/reports', label: '报表生成', available: false },
  { key: 'patients', to: '/patients', label: '病人管理', available: true },
  { key: 'medicineLocations', to: '/medicine-locations', label: '药品管理', available: true },
  { key: 'medicineSettings', to: '/medicine-settings', label: '药盒设置', available: false },
  { key: 'writeoff', to: '/writeoff', label: '销账', available: false },
  { key: 'operationLog', to: '/operation-log', label: '操作记录', available: false },
  { key: 'medicineDown', to: null, label: '药品下架', available: false },
  { key: 'restock', to: '/restock', label: '补药', available: false },
  { key: 'inventory', to: '/inventory', label: '库存查询', available: false },
  { key: 'prescriptions', to: '/prescriptions', label: '处方记录', available: true },
];
