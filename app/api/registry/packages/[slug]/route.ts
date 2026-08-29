import { getPackage } from "../../../../../lib/registry/registry";
import { packageResponse } from "../../../../../lib/registry/responses";

type PackageRouteContext = {
  readonly params: Promise<{
    readonly slug: string;
  }>;
};

export async function GET(_request: Request, context: PackageRouteContext) {
  const { slug } = await context.params;
  const item = getPackage(slug);
  return Response.json(packageResponse(item), {
    status: item === null ? 404 : 200,
  });
}
