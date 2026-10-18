-- Run from BeamNG's GE Lua console while the desired scene is open.
-- Captures state only; does not move cars or start playback.
local output = '/home/vinnavan/user/MegaProjects/IBM/scenarios/extended-90-degree-data-collection/extended-90-degree-data-collection.json'
local mgr = require('editor/drivePathEditor/splineMgr')
local data = {
  schema_version = 1,
  save_name = 'extended 90 degree data collection',
  mapName = core_levels.getLevelName(getMissionFilename()),
  tool = mgr.getToolPrefixStr(),
  splines = {}, vehicles = {},
  note = 'Native Drive Path Editor session plus car poses/configurations. Relink routes by linked_vehicle_name after respawning cars with new numeric IDs. User-named junction angle is not surveyed.'
}
assert(data.mapName == 'west_coast_usa', 'Expected West Coast USA; save cancelled')
local names = {}
for _, vehicle in ipairs(getAllVehicles()) do
  local p, q = vehicle:getPosition(), vehicle:getRotation()
  local f, u = vehicle:getDirectionVector(), vehicle:getDirectionVectorUp()
  local name, id = vehicle:getName(), vehicle:getID()
  names[id] = name
  data.vehicles[#data.vehicles + 1] = {
    name = name, id = id, model = vehicle:getJBeamFilename(),
    position_m = {p.x, p.y, p.z}, rotation_quat_xyzw = {q.x, q.y, q.z, q.w},
    forward = {f.x, f.y, f.z}, up = {u.x, u.y, u.z},
    config = core_vehicle_partmgmt.getConfigOfVehicle(id)
  }
end
for _, spline in ipairs(mgr.getDrivePathSplines()) do
  local saved = mgr.serializeDrivePathSpline(spline)
  saved.linked_vehicle_name = names[spline.linkVehId]
  data.splines[#data.splines + 1] = saved
end
assert(#data.splines >= 2, 'Expected at least two routes; save cancelled')
jsonWriteFile(output, data, true)
local readback = jsonReadFile(output)
assert(readback and #readback.splines == #data.splines and #readback.vehicles == #data.vehicles, 'Save readback failed')
log('I', 'UrielSceneSave', 'Saved extended 90 degree data collection: ' .. output)
print('Saved extended 90 degree data collection: ' .. output)
