import { packagesResponse } from "../../../../lib/registry/responses";
import { searchPackages } from "../../../../lib/registry/search";

export function GET(request: Request) {
  const url = new URL(request.url);
  return Response.json(
    packagesResponse(searchPackages(url.searchParams.get("q") ?? "")),
  );
}
