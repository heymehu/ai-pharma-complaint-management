import { api } from "@/lib/utils";

export async function downloadComplaintPdf(
  formData: Record<string, unknown>,
  filename?: string
) {
  const blob = await api<Blob>("/ai/pdf", {
    method: "POST",
    body: JSON.stringify({
      report_type: "Complaint Report",
      form_data: formData,
    }),
  });
  const id = (formData.complaint_id as string) || "complaint";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || `aivoa-${id.toLowerCase()}.pdf`;
  a.click();
  URL.revokeObjectURL(url);
}
