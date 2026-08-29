import { listPackages } from "../../../../lib/registry/registry";
import { packagesResponse } from "../../../../lib/registry/responses";

export function GET() {
  return Response.json(packagesResponse(listPackages()));
}
